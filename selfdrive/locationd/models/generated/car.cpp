#include "car.h"

namespace {
#define DIM 9
#define EDIM 9
#define MEDIM 9
typedef void (*Hfun)(double *, double *, double *);

double mass;

void set_mass(double x){ mass = x;}

double rotational_inertia;

void set_rotational_inertia(double x){ rotational_inertia = x;}

double center_to_front;

void set_center_to_front(double x){ center_to_front = x;}

double center_to_rear;

void set_center_to_rear(double x){ center_to_rear = x;}

double stiffness_front;

void set_stiffness_front(double x){ stiffness_front = x;}

double stiffness_rear;

void set_stiffness_rear(double x){ stiffness_rear = x;}
const static double MAHA_THRESH_25 = 3.8414588206941227;
const static double MAHA_THRESH_24 = 5.991464547107981;
const static double MAHA_THRESH_30 = 3.8414588206941227;
const static double MAHA_THRESH_26 = 3.8414588206941227;
const static double MAHA_THRESH_27 = 3.8414588206941227;
const static double MAHA_THRESH_29 = 3.8414588206941227;
const static double MAHA_THRESH_28 = 3.8414588206941227;
const static double MAHA_THRESH_31 = 3.8414588206941227;

/******************************************************************************
 *                      Code generated with SymPy 1.14.0                      *
 *                                                                            *
 *              See http://www.sympy.org/ for more information.               *
 *                                                                            *
 *                         This file is part of 'ekf'                         *
 ******************************************************************************/
void err_fun(double *nom_x, double *delta_x, double *out_5232047554535600109) {
   out_5232047554535600109[0] = delta_x[0] + nom_x[0];
   out_5232047554535600109[1] = delta_x[1] + nom_x[1];
   out_5232047554535600109[2] = delta_x[2] + nom_x[2];
   out_5232047554535600109[3] = delta_x[3] + nom_x[3];
   out_5232047554535600109[4] = delta_x[4] + nom_x[4];
   out_5232047554535600109[5] = delta_x[5] + nom_x[5];
   out_5232047554535600109[6] = delta_x[6] + nom_x[6];
   out_5232047554535600109[7] = delta_x[7] + nom_x[7];
   out_5232047554535600109[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_5926361318328117466) {
   out_5926361318328117466[0] = -nom_x[0] + true_x[0];
   out_5926361318328117466[1] = -nom_x[1] + true_x[1];
   out_5926361318328117466[2] = -nom_x[2] + true_x[2];
   out_5926361318328117466[3] = -nom_x[3] + true_x[3];
   out_5926361318328117466[4] = -nom_x[4] + true_x[4];
   out_5926361318328117466[5] = -nom_x[5] + true_x[5];
   out_5926361318328117466[6] = -nom_x[6] + true_x[6];
   out_5926361318328117466[7] = -nom_x[7] + true_x[7];
   out_5926361318328117466[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_8663045025294862621) {
   out_8663045025294862621[0] = 1.0;
   out_8663045025294862621[1] = 0.0;
   out_8663045025294862621[2] = 0.0;
   out_8663045025294862621[3] = 0.0;
   out_8663045025294862621[4] = 0.0;
   out_8663045025294862621[5] = 0.0;
   out_8663045025294862621[6] = 0.0;
   out_8663045025294862621[7] = 0.0;
   out_8663045025294862621[8] = 0.0;
   out_8663045025294862621[9] = 0.0;
   out_8663045025294862621[10] = 1.0;
   out_8663045025294862621[11] = 0.0;
   out_8663045025294862621[12] = 0.0;
   out_8663045025294862621[13] = 0.0;
   out_8663045025294862621[14] = 0.0;
   out_8663045025294862621[15] = 0.0;
   out_8663045025294862621[16] = 0.0;
   out_8663045025294862621[17] = 0.0;
   out_8663045025294862621[18] = 0.0;
   out_8663045025294862621[19] = 0.0;
   out_8663045025294862621[20] = 1.0;
   out_8663045025294862621[21] = 0.0;
   out_8663045025294862621[22] = 0.0;
   out_8663045025294862621[23] = 0.0;
   out_8663045025294862621[24] = 0.0;
   out_8663045025294862621[25] = 0.0;
   out_8663045025294862621[26] = 0.0;
   out_8663045025294862621[27] = 0.0;
   out_8663045025294862621[28] = 0.0;
   out_8663045025294862621[29] = 0.0;
   out_8663045025294862621[30] = 1.0;
   out_8663045025294862621[31] = 0.0;
   out_8663045025294862621[32] = 0.0;
   out_8663045025294862621[33] = 0.0;
   out_8663045025294862621[34] = 0.0;
   out_8663045025294862621[35] = 0.0;
   out_8663045025294862621[36] = 0.0;
   out_8663045025294862621[37] = 0.0;
   out_8663045025294862621[38] = 0.0;
   out_8663045025294862621[39] = 0.0;
   out_8663045025294862621[40] = 1.0;
   out_8663045025294862621[41] = 0.0;
   out_8663045025294862621[42] = 0.0;
   out_8663045025294862621[43] = 0.0;
   out_8663045025294862621[44] = 0.0;
   out_8663045025294862621[45] = 0.0;
   out_8663045025294862621[46] = 0.0;
   out_8663045025294862621[47] = 0.0;
   out_8663045025294862621[48] = 0.0;
   out_8663045025294862621[49] = 0.0;
   out_8663045025294862621[50] = 1.0;
   out_8663045025294862621[51] = 0.0;
   out_8663045025294862621[52] = 0.0;
   out_8663045025294862621[53] = 0.0;
   out_8663045025294862621[54] = 0.0;
   out_8663045025294862621[55] = 0.0;
   out_8663045025294862621[56] = 0.0;
   out_8663045025294862621[57] = 0.0;
   out_8663045025294862621[58] = 0.0;
   out_8663045025294862621[59] = 0.0;
   out_8663045025294862621[60] = 1.0;
   out_8663045025294862621[61] = 0.0;
   out_8663045025294862621[62] = 0.0;
   out_8663045025294862621[63] = 0.0;
   out_8663045025294862621[64] = 0.0;
   out_8663045025294862621[65] = 0.0;
   out_8663045025294862621[66] = 0.0;
   out_8663045025294862621[67] = 0.0;
   out_8663045025294862621[68] = 0.0;
   out_8663045025294862621[69] = 0.0;
   out_8663045025294862621[70] = 1.0;
   out_8663045025294862621[71] = 0.0;
   out_8663045025294862621[72] = 0.0;
   out_8663045025294862621[73] = 0.0;
   out_8663045025294862621[74] = 0.0;
   out_8663045025294862621[75] = 0.0;
   out_8663045025294862621[76] = 0.0;
   out_8663045025294862621[77] = 0.0;
   out_8663045025294862621[78] = 0.0;
   out_8663045025294862621[79] = 0.0;
   out_8663045025294862621[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_4712382669747920854) {
   out_4712382669747920854[0] = state[0];
   out_4712382669747920854[1] = state[1];
   out_4712382669747920854[2] = state[2];
   out_4712382669747920854[3] = state[3];
   out_4712382669747920854[4] = state[4];
   out_4712382669747920854[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_4712382669747920854[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_4712382669747920854[7] = state[7];
   out_4712382669747920854[8] = state[8];
}
void F_fun(double *state, double dt, double *out_6132820248099245599) {
   out_6132820248099245599[0] = 1;
   out_6132820248099245599[1] = 0;
   out_6132820248099245599[2] = 0;
   out_6132820248099245599[3] = 0;
   out_6132820248099245599[4] = 0;
   out_6132820248099245599[5] = 0;
   out_6132820248099245599[6] = 0;
   out_6132820248099245599[7] = 0;
   out_6132820248099245599[8] = 0;
   out_6132820248099245599[9] = 0;
   out_6132820248099245599[10] = 1;
   out_6132820248099245599[11] = 0;
   out_6132820248099245599[12] = 0;
   out_6132820248099245599[13] = 0;
   out_6132820248099245599[14] = 0;
   out_6132820248099245599[15] = 0;
   out_6132820248099245599[16] = 0;
   out_6132820248099245599[17] = 0;
   out_6132820248099245599[18] = 0;
   out_6132820248099245599[19] = 0;
   out_6132820248099245599[20] = 1;
   out_6132820248099245599[21] = 0;
   out_6132820248099245599[22] = 0;
   out_6132820248099245599[23] = 0;
   out_6132820248099245599[24] = 0;
   out_6132820248099245599[25] = 0;
   out_6132820248099245599[26] = 0;
   out_6132820248099245599[27] = 0;
   out_6132820248099245599[28] = 0;
   out_6132820248099245599[29] = 0;
   out_6132820248099245599[30] = 1;
   out_6132820248099245599[31] = 0;
   out_6132820248099245599[32] = 0;
   out_6132820248099245599[33] = 0;
   out_6132820248099245599[34] = 0;
   out_6132820248099245599[35] = 0;
   out_6132820248099245599[36] = 0;
   out_6132820248099245599[37] = 0;
   out_6132820248099245599[38] = 0;
   out_6132820248099245599[39] = 0;
   out_6132820248099245599[40] = 1;
   out_6132820248099245599[41] = 0;
   out_6132820248099245599[42] = 0;
   out_6132820248099245599[43] = 0;
   out_6132820248099245599[44] = 0;
   out_6132820248099245599[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_6132820248099245599[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_6132820248099245599[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6132820248099245599[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6132820248099245599[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_6132820248099245599[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_6132820248099245599[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_6132820248099245599[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_6132820248099245599[53] = -9.8100000000000005*dt;
   out_6132820248099245599[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_6132820248099245599[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_6132820248099245599[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6132820248099245599[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6132820248099245599[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_6132820248099245599[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_6132820248099245599[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_6132820248099245599[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6132820248099245599[62] = 0;
   out_6132820248099245599[63] = 0;
   out_6132820248099245599[64] = 0;
   out_6132820248099245599[65] = 0;
   out_6132820248099245599[66] = 0;
   out_6132820248099245599[67] = 0;
   out_6132820248099245599[68] = 0;
   out_6132820248099245599[69] = 0;
   out_6132820248099245599[70] = 1;
   out_6132820248099245599[71] = 0;
   out_6132820248099245599[72] = 0;
   out_6132820248099245599[73] = 0;
   out_6132820248099245599[74] = 0;
   out_6132820248099245599[75] = 0;
   out_6132820248099245599[76] = 0;
   out_6132820248099245599[77] = 0;
   out_6132820248099245599[78] = 0;
   out_6132820248099245599[79] = 0;
   out_6132820248099245599[80] = 1;
}
void h_25(double *state, double *unused, double *out_8954572363719808224) {
   out_8954572363719808224[0] = state[6];
}
void H_25(double *state, double *unused, double *out_6260718398425197318) {
   out_6260718398425197318[0] = 0;
   out_6260718398425197318[1] = 0;
   out_6260718398425197318[2] = 0;
   out_6260718398425197318[3] = 0;
   out_6260718398425197318[4] = 0;
   out_6260718398425197318[5] = 0;
   out_6260718398425197318[6] = 1;
   out_6260718398425197318[7] = 0;
   out_6260718398425197318[8] = 0;
}
void h_24(double *state, double *unused, double *out_573451915361062774) {
   out_573451915361062774[0] = state[4];
   out_573451915361062774[1] = state[5];
}
void H_24(double *state, double *unused, double *out_8433367997430696884) {
   out_8433367997430696884[0] = 0;
   out_8433367997430696884[1] = 0;
   out_8433367997430696884[2] = 0;
   out_8433367997430696884[3] = 0;
   out_8433367997430696884[4] = 1;
   out_8433367997430696884[5] = 0;
   out_8433367997430696884[6] = 0;
   out_8433367997430696884[7] = 0;
   out_8433367997430696884[8] = 0;
   out_8433367997430696884[9] = 0;
   out_8433367997430696884[10] = 0;
   out_8433367997430696884[11] = 0;
   out_8433367997430696884[12] = 0;
   out_8433367997430696884[13] = 0;
   out_8433367997430696884[14] = 1;
   out_8433367997430696884[15] = 0;
   out_8433367997430696884[16] = 0;
   out_8433367997430696884[17] = 0;
}
void h_30(double *state, double *unused, double *out_995511028726003400) {
   out_995511028726003400[0] = state[4];
}
void H_30(double *state, double *unused, double *out_655971943066419437) {
   out_655971943066419437[0] = 0;
   out_655971943066419437[1] = 0;
   out_655971943066419437[2] = 0;
   out_655971943066419437[3] = 0;
   out_655971943066419437[4] = 1;
   out_655971943066419437[5] = 0;
   out_655971943066419437[6] = 0;
   out_655971943066419437[7] = 0;
   out_655971943066419437[8] = 0;
}
void h_26(double *state, double *unused, double *out_8430654463154704213) {
   out_8430654463154704213[0] = state[7];
}
void H_26(double *state, double *unused, double *out_8444522356410298074) {
   out_8444522356410298074[0] = 0;
   out_8444522356410298074[1] = 0;
   out_8444522356410298074[2] = 0;
   out_8444522356410298074[3] = 0;
   out_8444522356410298074[4] = 0;
   out_8444522356410298074[5] = 0;
   out_8444522356410298074[6] = 0;
   out_8444522356410298074[7] = 1;
   out_8444522356410298074[8] = 0;
}
void h_27(double *state, double *unused, double *out_8548661857088080957) {
   out_8548661857088080957[0] = state[3];
}
void H_27(double *state, double *unused, double *out_1518791368734005474) {
   out_1518791368734005474[0] = 0;
   out_1518791368734005474[1] = 0;
   out_1518791368734005474[2] = 0;
   out_1518791368734005474[3] = 1;
   out_1518791368734005474[4] = 0;
   out_1518791368734005474[5] = 0;
   out_1518791368734005474[6] = 0;
   out_1518791368734005474[7] = 0;
   out_1518791368734005474[8] = 0;
}
void h_29(double *state, double *unused, double *out_589055427595770225) {
   out_589055427595770225[0] = state[1];
}
void H_29(double *state, double *unused, double *out_3232154095603556507) {
   out_3232154095603556507[0] = 0;
   out_3232154095603556507[1] = 1;
   out_3232154095603556507[2] = 0;
   out_3232154095603556507[3] = 0;
   out_3232154095603556507[4] = 0;
   out_3232154095603556507[5] = 0;
   out_3232154095603556507[6] = 0;
   out_3232154095603556507[7] = 0;
   out_3232154095603556507[8] = 0;
}
void h_28(double *state, double *unused, double *out_7867012193673341893) {
   out_7867012193673341893[0] = state[0];
}
void H_28(double *state, double *unused, double *out_8314553112673087081) {
   out_8314553112673087081[0] = 1;
   out_8314553112673087081[1] = 0;
   out_8314553112673087081[2] = 0;
   out_8314553112673087081[3] = 0;
   out_8314553112673087081[4] = 0;
   out_8314553112673087081[5] = 0;
   out_8314553112673087081[6] = 0;
   out_8314553112673087081[7] = 0;
   out_8314553112673087081[8] = 0;
}
void h_31(double *state, double *unused, double *out_2027016737343401600) {
   out_2027016737343401600[0] = state[8];
}
void H_31(double *state, double *unused, double *out_6230072436548236890) {
   out_6230072436548236890[0] = 0;
   out_6230072436548236890[1] = 0;
   out_6230072436548236890[2] = 0;
   out_6230072436548236890[3] = 0;
   out_6230072436548236890[4] = 0;
   out_6230072436548236890[5] = 0;
   out_6230072436548236890[6] = 0;
   out_6230072436548236890[7] = 0;
   out_6230072436548236890[8] = 1;
}
#include <eigen3/Eigen/Dense>
#include <iostream>

typedef Eigen::Matrix<double, DIM, DIM, Eigen::RowMajor> DDM;
typedef Eigen::Matrix<double, EDIM, EDIM, Eigen::RowMajor> EEM;
typedef Eigen::Matrix<double, DIM, EDIM, Eigen::RowMajor> DEM;

void predict(double *in_x, double *in_P, double *in_Q, double dt) {
  typedef Eigen::Matrix<double, MEDIM, MEDIM, Eigen::RowMajor> RRM;

  double nx[DIM] = {0};
  double in_F[EDIM*EDIM] = {0};

  // functions from sympy
  f_fun(in_x, dt, nx);
  F_fun(in_x, dt, in_F);


  EEM F(in_F);
  EEM P(in_P);
  EEM Q(in_Q);

  RRM F_main = F.topLeftCorner(MEDIM, MEDIM);
  P.topLeftCorner(MEDIM, MEDIM) = (F_main * P.topLeftCorner(MEDIM, MEDIM)) * F_main.transpose();
  P.topRightCorner(MEDIM, EDIM - MEDIM) = F_main * P.topRightCorner(MEDIM, EDIM - MEDIM);
  P.bottomLeftCorner(EDIM - MEDIM, MEDIM) = P.bottomLeftCorner(EDIM - MEDIM, MEDIM) * F_main.transpose();

  P = P + dt*Q;

  // copy out state
  memcpy(in_x, nx, DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
}

// note: extra_args dim only correct when null space projecting
// otherwise 1
template <int ZDIM, int EADIM, bool MAHA_TEST>
void update(double *in_x, double *in_P, Hfun h_fun, Hfun H_fun, Hfun Hea_fun, double *in_z, double *in_R, double *in_ea, double MAHA_THRESHOLD) {
  typedef Eigen::Matrix<double, ZDIM, ZDIM, Eigen::RowMajor> ZZM;
  typedef Eigen::Matrix<double, ZDIM, DIM, Eigen::RowMajor> ZDM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, EDIM, Eigen::RowMajor> XEM;
  //typedef Eigen::Matrix<double, EDIM, ZDIM, Eigen::RowMajor> EZM;
  typedef Eigen::Matrix<double, Eigen::Dynamic, 1> X1M;
  typedef Eigen::Matrix<double, Eigen::Dynamic, Eigen::Dynamic, Eigen::RowMajor> XXM;

  double in_hx[ZDIM] = {0};
  double in_H[ZDIM * DIM] = {0};
  double in_H_mod[EDIM * DIM] = {0};
  double delta_x[EDIM] = {0};
  double x_new[DIM] = {0};


  // state x, P
  Eigen::Matrix<double, ZDIM, 1> z(in_z);
  EEM P(in_P);
  ZZM pre_R(in_R);

  // functions from sympy
  h_fun(in_x, in_ea, in_hx);
  H_fun(in_x, in_ea, in_H);
  ZDM pre_H(in_H);

  // get y (y = z - hx)
  Eigen::Matrix<double, ZDIM, 1> pre_y(in_hx); pre_y = z - pre_y;
  X1M y; XXM H; XXM R;
  if (Hea_fun){
    typedef Eigen::Matrix<double, ZDIM, EADIM, Eigen::RowMajor> ZAM;
    double in_Hea[ZDIM * EADIM] = {0};
    Hea_fun(in_x, in_ea, in_Hea);
    ZAM Hea(in_Hea);
    XXM A = Hea.transpose().fullPivLu().kernel();


    y = A.transpose() * pre_y;
    H = A.transpose() * pre_H;
    R = A.transpose() * pre_R * A;
  } else {
    y = pre_y;
    H = pre_H;
    R = pre_R;
  }
  // get modified H
  H_mod_fun(in_x, in_H_mod);
  DEM H_mod(in_H_mod);
  XEM H_err = H * H_mod;

  // Do mahalobis distance test
  if (MAHA_TEST){
    XXM a = (H_err * P * H_err.transpose() + R).inverse();
    double maha_dist = y.transpose() * a * y;
    if (maha_dist > MAHA_THRESHOLD){
      R = 1.0e16 * R;
    }
  }

  // Outlier resilient weighting
  double weight = 1;//(1.5)/(1 + y.squaredNorm()/R.sum());

  // kalman gains and I_KH
  XXM S = ((H_err * P) * H_err.transpose()) + R/weight;
  XEM KT = S.fullPivLu().solve(H_err * P.transpose());
  //EZM K = KT.transpose(); TODO: WHY DOES THIS NOT COMPILE?
  //EZM K = S.fullPivLu().solve(H_err * P.transpose()).transpose();
  //std::cout << "Here is the matrix rot:\n" << K << std::endl;
  EEM I_KH = Eigen::Matrix<double, EDIM, EDIM>::Identity() - (KT.transpose() * H_err);

  // update state by injecting dx
  Eigen::Matrix<double, EDIM, 1> dx(delta_x);
  dx  = (KT.transpose() * y);
  memcpy(delta_x, dx.data(), EDIM * sizeof(double));
  err_fun(in_x, delta_x, x_new);
  Eigen::Matrix<double, DIM, 1> x(x_new);

  // update cov
  P = ((I_KH * P) * I_KH.transpose()) + ((KT.transpose() * R) * KT);

  // copy out state
  memcpy(in_x, x.data(), DIM * sizeof(double));
  memcpy(in_P, P.data(), EDIM * EDIM * sizeof(double));
  memcpy(in_z, y.data(), y.rows() * sizeof(double));
}




}
extern "C" {

void car_update_25(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_25, H_25, NULL, in_z, in_R, in_ea, MAHA_THRESH_25);
}
void car_update_24(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<2, 3, 0>(in_x, in_P, h_24, H_24, NULL, in_z, in_R, in_ea, MAHA_THRESH_24);
}
void car_update_30(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_30, H_30, NULL, in_z, in_R, in_ea, MAHA_THRESH_30);
}
void car_update_26(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_26, H_26, NULL, in_z, in_R, in_ea, MAHA_THRESH_26);
}
void car_update_27(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_27, H_27, NULL, in_z, in_R, in_ea, MAHA_THRESH_27);
}
void car_update_29(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_29, H_29, NULL, in_z, in_R, in_ea, MAHA_THRESH_29);
}
void car_update_28(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_28, H_28, NULL, in_z, in_R, in_ea, MAHA_THRESH_28);
}
void car_update_31(double *in_x, double *in_P, double *in_z, double *in_R, double *in_ea) {
  update<1, 3, 0>(in_x, in_P, h_31, H_31, NULL, in_z, in_R, in_ea, MAHA_THRESH_31);
}
void car_err_fun(double *nom_x, double *delta_x, double *out_5232047554535600109) {
  err_fun(nom_x, delta_x, out_5232047554535600109);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_5926361318328117466) {
  inv_err_fun(nom_x, true_x, out_5926361318328117466);
}
void car_H_mod_fun(double *state, double *out_8663045025294862621) {
  H_mod_fun(state, out_8663045025294862621);
}
void car_f_fun(double *state, double dt, double *out_4712382669747920854) {
  f_fun(state,  dt, out_4712382669747920854);
}
void car_F_fun(double *state, double dt, double *out_6132820248099245599) {
  F_fun(state,  dt, out_6132820248099245599);
}
void car_h_25(double *state, double *unused, double *out_8954572363719808224) {
  h_25(state, unused, out_8954572363719808224);
}
void car_H_25(double *state, double *unused, double *out_6260718398425197318) {
  H_25(state, unused, out_6260718398425197318);
}
void car_h_24(double *state, double *unused, double *out_573451915361062774) {
  h_24(state, unused, out_573451915361062774);
}
void car_H_24(double *state, double *unused, double *out_8433367997430696884) {
  H_24(state, unused, out_8433367997430696884);
}
void car_h_30(double *state, double *unused, double *out_995511028726003400) {
  h_30(state, unused, out_995511028726003400);
}
void car_H_30(double *state, double *unused, double *out_655971943066419437) {
  H_30(state, unused, out_655971943066419437);
}
void car_h_26(double *state, double *unused, double *out_8430654463154704213) {
  h_26(state, unused, out_8430654463154704213);
}
void car_H_26(double *state, double *unused, double *out_8444522356410298074) {
  H_26(state, unused, out_8444522356410298074);
}
void car_h_27(double *state, double *unused, double *out_8548661857088080957) {
  h_27(state, unused, out_8548661857088080957);
}
void car_H_27(double *state, double *unused, double *out_1518791368734005474) {
  H_27(state, unused, out_1518791368734005474);
}
void car_h_29(double *state, double *unused, double *out_589055427595770225) {
  h_29(state, unused, out_589055427595770225);
}
void car_H_29(double *state, double *unused, double *out_3232154095603556507) {
  H_29(state, unused, out_3232154095603556507);
}
void car_h_28(double *state, double *unused, double *out_7867012193673341893) {
  h_28(state, unused, out_7867012193673341893);
}
void car_H_28(double *state, double *unused, double *out_8314553112673087081) {
  H_28(state, unused, out_8314553112673087081);
}
void car_h_31(double *state, double *unused, double *out_2027016737343401600) {
  h_31(state, unused, out_2027016737343401600);
}
void car_H_31(double *state, double *unused, double *out_6230072436548236890) {
  H_31(state, unused, out_6230072436548236890);
}
void car_predict(double *in_x, double *in_P, double *in_Q, double dt) {
  predict(in_x, in_P, in_Q, dt);
}
void car_set_mass(double x) {
  set_mass(x);
}
void car_set_rotational_inertia(double x) {
  set_rotational_inertia(x);
}
void car_set_center_to_front(double x) {
  set_center_to_front(x);
}
void car_set_center_to_rear(double x) {
  set_center_to_rear(x);
}
void car_set_stiffness_front(double x) {
  set_stiffness_front(x);
}
void car_set_stiffness_rear(double x) {
  set_stiffness_rear(x);
}
}

const EKF car = {
  .name = "car",
  .kinds = { 25, 24, 30, 26, 27, 29, 28, 31 },
  .feature_kinds = {  },
  .f_fun = car_f_fun,
  .F_fun = car_F_fun,
  .err_fun = car_err_fun,
  .inv_err_fun = car_inv_err_fun,
  .H_mod_fun = car_H_mod_fun,
  .predict = car_predict,
  .hs = {
    { 25, car_h_25 },
    { 24, car_h_24 },
    { 30, car_h_30 },
    { 26, car_h_26 },
    { 27, car_h_27 },
    { 29, car_h_29 },
    { 28, car_h_28 },
    { 31, car_h_31 },
  },
  .Hs = {
    { 25, car_H_25 },
    { 24, car_H_24 },
    { 30, car_H_30 },
    { 26, car_H_26 },
    { 27, car_H_27 },
    { 29, car_H_29 },
    { 28, car_H_28 },
    { 31, car_H_31 },
  },
  .updates = {
    { 25, car_update_25 },
    { 24, car_update_24 },
    { 30, car_update_30 },
    { 26, car_update_26 },
    { 27, car_update_27 },
    { 29, car_update_29 },
    { 28, car_update_28 },
    { 31, car_update_31 },
  },
  .Hes = {
  },
  .sets = {
    { "mass", car_set_mass },
    { "rotational_inertia", car_set_rotational_inertia },
    { "center_to_front", car_set_center_to_front },
    { "center_to_rear", car_set_center_to_rear },
    { "stiffness_front", car_set_stiffness_front },
    { "stiffness_rear", car_set_stiffness_rear },
  },
  .extra_routines = {
  },
};

ekf_lib_init(car)
