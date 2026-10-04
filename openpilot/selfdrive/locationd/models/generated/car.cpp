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
void err_fun(double *nom_x, double *delta_x, double *out_4155166221753319167) {
   out_4155166221753319167[0] = delta_x[0] + nom_x[0];
   out_4155166221753319167[1] = delta_x[1] + nom_x[1];
   out_4155166221753319167[2] = delta_x[2] + nom_x[2];
   out_4155166221753319167[3] = delta_x[3] + nom_x[3];
   out_4155166221753319167[4] = delta_x[4] + nom_x[4];
   out_4155166221753319167[5] = delta_x[5] + nom_x[5];
   out_4155166221753319167[6] = delta_x[6] + nom_x[6];
   out_4155166221753319167[7] = delta_x[7] + nom_x[7];
   out_4155166221753319167[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_6258424399114082833) {
   out_6258424399114082833[0] = -nom_x[0] + true_x[0];
   out_6258424399114082833[1] = -nom_x[1] + true_x[1];
   out_6258424399114082833[2] = -nom_x[2] + true_x[2];
   out_6258424399114082833[3] = -nom_x[3] + true_x[3];
   out_6258424399114082833[4] = -nom_x[4] + true_x[4];
   out_6258424399114082833[5] = -nom_x[5] + true_x[5];
   out_6258424399114082833[6] = -nom_x[6] + true_x[6];
   out_6258424399114082833[7] = -nom_x[7] + true_x[7];
   out_6258424399114082833[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_9207883978122540712) {
   out_9207883978122540712[0] = 1.0;
   out_9207883978122540712[1] = 0.0;
   out_9207883978122540712[2] = 0.0;
   out_9207883978122540712[3] = 0.0;
   out_9207883978122540712[4] = 0.0;
   out_9207883978122540712[5] = 0.0;
   out_9207883978122540712[6] = 0.0;
   out_9207883978122540712[7] = 0.0;
   out_9207883978122540712[8] = 0.0;
   out_9207883978122540712[9] = 0.0;
   out_9207883978122540712[10] = 1.0;
   out_9207883978122540712[11] = 0.0;
   out_9207883978122540712[12] = 0.0;
   out_9207883978122540712[13] = 0.0;
   out_9207883978122540712[14] = 0.0;
   out_9207883978122540712[15] = 0.0;
   out_9207883978122540712[16] = 0.0;
   out_9207883978122540712[17] = 0.0;
   out_9207883978122540712[18] = 0.0;
   out_9207883978122540712[19] = 0.0;
   out_9207883978122540712[20] = 1.0;
   out_9207883978122540712[21] = 0.0;
   out_9207883978122540712[22] = 0.0;
   out_9207883978122540712[23] = 0.0;
   out_9207883978122540712[24] = 0.0;
   out_9207883978122540712[25] = 0.0;
   out_9207883978122540712[26] = 0.0;
   out_9207883978122540712[27] = 0.0;
   out_9207883978122540712[28] = 0.0;
   out_9207883978122540712[29] = 0.0;
   out_9207883978122540712[30] = 1.0;
   out_9207883978122540712[31] = 0.0;
   out_9207883978122540712[32] = 0.0;
   out_9207883978122540712[33] = 0.0;
   out_9207883978122540712[34] = 0.0;
   out_9207883978122540712[35] = 0.0;
   out_9207883978122540712[36] = 0.0;
   out_9207883978122540712[37] = 0.0;
   out_9207883978122540712[38] = 0.0;
   out_9207883978122540712[39] = 0.0;
   out_9207883978122540712[40] = 1.0;
   out_9207883978122540712[41] = 0.0;
   out_9207883978122540712[42] = 0.0;
   out_9207883978122540712[43] = 0.0;
   out_9207883978122540712[44] = 0.0;
   out_9207883978122540712[45] = 0.0;
   out_9207883978122540712[46] = 0.0;
   out_9207883978122540712[47] = 0.0;
   out_9207883978122540712[48] = 0.0;
   out_9207883978122540712[49] = 0.0;
   out_9207883978122540712[50] = 1.0;
   out_9207883978122540712[51] = 0.0;
   out_9207883978122540712[52] = 0.0;
   out_9207883978122540712[53] = 0.0;
   out_9207883978122540712[54] = 0.0;
   out_9207883978122540712[55] = 0.0;
   out_9207883978122540712[56] = 0.0;
   out_9207883978122540712[57] = 0.0;
   out_9207883978122540712[58] = 0.0;
   out_9207883978122540712[59] = 0.0;
   out_9207883978122540712[60] = 1.0;
   out_9207883978122540712[61] = 0.0;
   out_9207883978122540712[62] = 0.0;
   out_9207883978122540712[63] = 0.0;
   out_9207883978122540712[64] = 0.0;
   out_9207883978122540712[65] = 0.0;
   out_9207883978122540712[66] = 0.0;
   out_9207883978122540712[67] = 0.0;
   out_9207883978122540712[68] = 0.0;
   out_9207883978122540712[69] = 0.0;
   out_9207883978122540712[70] = 1.0;
   out_9207883978122540712[71] = 0.0;
   out_9207883978122540712[72] = 0.0;
   out_9207883978122540712[73] = 0.0;
   out_9207883978122540712[74] = 0.0;
   out_9207883978122540712[75] = 0.0;
   out_9207883978122540712[76] = 0.0;
   out_9207883978122540712[77] = 0.0;
   out_9207883978122540712[78] = 0.0;
   out_9207883978122540712[79] = 0.0;
   out_9207883978122540712[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_6099552525591428416) {
   out_6099552525591428416[0] = state[0];
   out_6099552525591428416[1] = state[1];
   out_6099552525591428416[2] = state[2];
   out_6099552525591428416[3] = state[3];
   out_6099552525591428416[4] = state[4];
   out_6099552525591428416[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_6099552525591428416[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_6099552525591428416[7] = state[7];
   out_6099552525591428416[8] = state[8];
}
void F_fun(double *state, double dt, double *out_6907019441075095165) {
   out_6907019441075095165[0] = 1;
   out_6907019441075095165[1] = 0;
   out_6907019441075095165[2] = 0;
   out_6907019441075095165[3] = 0;
   out_6907019441075095165[4] = 0;
   out_6907019441075095165[5] = 0;
   out_6907019441075095165[6] = 0;
   out_6907019441075095165[7] = 0;
   out_6907019441075095165[8] = 0;
   out_6907019441075095165[9] = 0;
   out_6907019441075095165[10] = 1;
   out_6907019441075095165[11] = 0;
   out_6907019441075095165[12] = 0;
   out_6907019441075095165[13] = 0;
   out_6907019441075095165[14] = 0;
   out_6907019441075095165[15] = 0;
   out_6907019441075095165[16] = 0;
   out_6907019441075095165[17] = 0;
   out_6907019441075095165[18] = 0;
   out_6907019441075095165[19] = 0;
   out_6907019441075095165[20] = 1;
   out_6907019441075095165[21] = 0;
   out_6907019441075095165[22] = 0;
   out_6907019441075095165[23] = 0;
   out_6907019441075095165[24] = 0;
   out_6907019441075095165[25] = 0;
   out_6907019441075095165[26] = 0;
   out_6907019441075095165[27] = 0;
   out_6907019441075095165[28] = 0;
   out_6907019441075095165[29] = 0;
   out_6907019441075095165[30] = 1;
   out_6907019441075095165[31] = 0;
   out_6907019441075095165[32] = 0;
   out_6907019441075095165[33] = 0;
   out_6907019441075095165[34] = 0;
   out_6907019441075095165[35] = 0;
   out_6907019441075095165[36] = 0;
   out_6907019441075095165[37] = 0;
   out_6907019441075095165[38] = 0;
   out_6907019441075095165[39] = 0;
   out_6907019441075095165[40] = 1;
   out_6907019441075095165[41] = 0;
   out_6907019441075095165[42] = 0;
   out_6907019441075095165[43] = 0;
   out_6907019441075095165[44] = 0;
   out_6907019441075095165[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_6907019441075095165[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_6907019441075095165[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6907019441075095165[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_6907019441075095165[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_6907019441075095165[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_6907019441075095165[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_6907019441075095165[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_6907019441075095165[53] = -9.8100000000000005*dt;
   out_6907019441075095165[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_6907019441075095165[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_6907019441075095165[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6907019441075095165[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6907019441075095165[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_6907019441075095165[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_6907019441075095165[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_6907019441075095165[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_6907019441075095165[62] = 0;
   out_6907019441075095165[63] = 0;
   out_6907019441075095165[64] = 0;
   out_6907019441075095165[65] = 0;
   out_6907019441075095165[66] = 0;
   out_6907019441075095165[67] = 0;
   out_6907019441075095165[68] = 0;
   out_6907019441075095165[69] = 0;
   out_6907019441075095165[70] = 1;
   out_6907019441075095165[71] = 0;
   out_6907019441075095165[72] = 0;
   out_6907019441075095165[73] = 0;
   out_6907019441075095165[74] = 0;
   out_6907019441075095165[75] = 0;
   out_6907019441075095165[76] = 0;
   out_6907019441075095165[77] = 0;
   out_6907019441075095165[78] = 0;
   out_6907019441075095165[79] = 0;
   out_6907019441075095165[80] = 1;
}
void h_25(double *state, double *unused, double *out_7654255320318543180) {
   out_7654255320318543180[0] = state[6];
}
void H_25(double *state, double *unused, double *out_45671869674773667) {
   out_45671869674773667[0] = 0;
   out_45671869674773667[1] = 0;
   out_45671869674773667[2] = 0;
   out_45671869674773667[3] = 0;
   out_45671869674773667[4] = 0;
   out_45671869674773667[5] = 0;
   out_45671869674773667[6] = 1;
   out_45671869674773667[7] = 0;
   out_45671869674773667[8] = 0;
}
void h_24(double *state, double *unused, double *out_3125065132614720384) {
   out_3125065132614720384[0] = state[4];
   out_3125065132614720384[1] = state[5];
}
void H_24(double *state, double *unused, double *out_2126977729330725899) {
   out_2126977729330725899[0] = 0;
   out_2126977729330725899[1] = 0;
   out_2126977729330725899[2] = 0;
   out_2126977729330725899[3] = 0;
   out_2126977729330725899[4] = 1;
   out_2126977729330725899[5] = 0;
   out_2126977729330725899[6] = 0;
   out_2126977729330725899[7] = 0;
   out_2126977729330725899[8] = 0;
   out_2126977729330725899[9] = 0;
   out_2126977729330725899[10] = 0;
   out_2126977729330725899[11] = 0;
   out_2126977729330725899[12] = 0;
   out_2126977729330725899[13] = 0;
   out_2126977729330725899[14] = 1;
   out_2126977729330725899[15] = 0;
   out_2126977729330725899[16] = 0;
   out_2126977729330725899[17] = 0;
}
void h_30(double *state, double *unused, double *out_2295828072127268444) {
   out_2295828072127268444[0] = state[4];
}
void H_30(double *state, double *unused, double *out_2564004828182022294) {
   out_2564004828182022294[0] = 0;
   out_2564004828182022294[1] = 0;
   out_2564004828182022294[2] = 0;
   out_2564004828182022294[3] = 0;
   out_2564004828182022294[4] = 1;
   out_2564004828182022294[5] = 0;
   out_2564004828182022294[6] = 0;
   out_2564004828182022294[7] = 0;
   out_2564004828182022294[8] = 0;
}
void h_26(double *state, double *unused, double *out_5606219983362431125) {
   out_5606219983362431125[0] = state[7];
}
void H_26(double *state, double *unused, double *out_3695831449199282557) {
   out_3695831449199282557[0] = 0;
   out_3695831449199282557[1] = 0;
   out_3695831449199282557[2] = 0;
   out_3695831449199282557[3] = 0;
   out_3695831449199282557[4] = 0;
   out_3695831449199282557[5] = 0;
   out_3695831449199282557[6] = 0;
   out_3695831449199282557[7] = 1;
   out_3695831449199282557[8] = 0;
}
void h_27(double *state, double *unused, double *out_3256303239036914168) {
   out_3256303239036914168[0] = state[3];
}
void H_27(double *state, double *unused, double *out_4787598899365965511) {
   out_4787598899365965511[0] = 0;
   out_4787598899365965511[1] = 0;
   out_4787598899365965511[2] = 0;
   out_4787598899365965511[3] = 1;
   out_4787598899365965511[4] = 0;
   out_4787598899365965511[5] = 0;
   out_4787598899365965511[6] = 0;
   out_4787598899365965511[7] = 0;
   out_4787598899365965511[8] = 0;
}
void h_29(double *state, double *unused, double *out_7297501339788114089) {
   out_7297501339788114089[0] = state[1];
}
void H_29(double *state, double *unused, double *out_3074236172496414478) {
   out_3074236172496414478[0] = 0;
   out_3074236172496414478[1] = 1;
   out_3074236172496414478[2] = 0;
   out_3074236172496414478[3] = 0;
   out_3074236172496414478[4] = 0;
   out_3074236172496414478[5] = 0;
   out_3074236172496414478[6] = 0;
   out_3074236172496414478[7] = 0;
   out_3074236172496414478[8] = 0;
}
void h_28(double *state, double *unused, double *out_6293089290481246853) {
   out_6293089290481246853[0] = state[0];
}
void H_28(double *state, double *unused, double *out_2008162844573116096) {
   out_2008162844573116096[0] = 1;
   out_2008162844573116096[1] = 0;
   out_2008162844573116096[2] = 0;
   out_2008162844573116096[3] = 0;
   out_2008162844573116096[4] = 0;
   out_2008162844573116096[5] = 0;
   out_2008162844573116096[6] = 0;
   out_2008162844573116096[7] = 0;
   out_2008162844573116096[8] = 0;
}
void h_31(double *state, double *unused, double *out_1487141280347408877) {
   out_1487141280347408877[0] = state[8];
}
void H_31(double *state, double *unused, double *out_76317831551734095) {
   out_76317831551734095[0] = 0;
   out_76317831551734095[1] = 0;
   out_76317831551734095[2] = 0;
   out_76317831551734095[3] = 0;
   out_76317831551734095[4] = 0;
   out_76317831551734095[5] = 0;
   out_76317831551734095[6] = 0;
   out_76317831551734095[7] = 0;
   out_76317831551734095[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_4155166221753319167) {
  err_fun(nom_x, delta_x, out_4155166221753319167);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_6258424399114082833) {
  inv_err_fun(nom_x, true_x, out_6258424399114082833);
}
void car_H_mod_fun(double *state, double *out_9207883978122540712) {
  H_mod_fun(state, out_9207883978122540712);
}
void car_f_fun(double *state, double dt, double *out_6099552525591428416) {
  f_fun(state,  dt, out_6099552525591428416);
}
void car_F_fun(double *state, double dt, double *out_6907019441075095165) {
  F_fun(state,  dt, out_6907019441075095165);
}
void car_h_25(double *state, double *unused, double *out_7654255320318543180) {
  h_25(state, unused, out_7654255320318543180);
}
void car_H_25(double *state, double *unused, double *out_45671869674773667) {
  H_25(state, unused, out_45671869674773667);
}
void car_h_24(double *state, double *unused, double *out_3125065132614720384) {
  h_24(state, unused, out_3125065132614720384);
}
void car_H_24(double *state, double *unused, double *out_2126977729330725899) {
  H_24(state, unused, out_2126977729330725899);
}
void car_h_30(double *state, double *unused, double *out_2295828072127268444) {
  h_30(state, unused, out_2295828072127268444);
}
void car_H_30(double *state, double *unused, double *out_2564004828182022294) {
  H_30(state, unused, out_2564004828182022294);
}
void car_h_26(double *state, double *unused, double *out_5606219983362431125) {
  h_26(state, unused, out_5606219983362431125);
}
void car_H_26(double *state, double *unused, double *out_3695831449199282557) {
  H_26(state, unused, out_3695831449199282557);
}
void car_h_27(double *state, double *unused, double *out_3256303239036914168) {
  h_27(state, unused, out_3256303239036914168);
}
void car_H_27(double *state, double *unused, double *out_4787598899365965511) {
  H_27(state, unused, out_4787598899365965511);
}
void car_h_29(double *state, double *unused, double *out_7297501339788114089) {
  h_29(state, unused, out_7297501339788114089);
}
void car_H_29(double *state, double *unused, double *out_3074236172496414478) {
  H_29(state, unused, out_3074236172496414478);
}
void car_h_28(double *state, double *unused, double *out_6293089290481246853) {
  h_28(state, unused, out_6293089290481246853);
}
void car_H_28(double *state, double *unused, double *out_2008162844573116096) {
  H_28(state, unused, out_2008162844573116096);
}
void car_h_31(double *state, double *unused, double *out_1487141280347408877) {
  h_31(state, unused, out_1487141280347408877);
}
void car_H_31(double *state, double *unused, double *out_76317831551734095) {
  H_31(state, unused, out_76317831551734095);
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
