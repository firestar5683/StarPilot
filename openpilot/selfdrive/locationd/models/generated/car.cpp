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
void err_fun(double *nom_x, double *delta_x, double *out_3365569118000208058) {
   out_3365569118000208058[0] = delta_x[0] + nom_x[0];
   out_3365569118000208058[1] = delta_x[1] + nom_x[1];
   out_3365569118000208058[2] = delta_x[2] + nom_x[2];
   out_3365569118000208058[3] = delta_x[3] + nom_x[3];
   out_3365569118000208058[4] = delta_x[4] + nom_x[4];
   out_3365569118000208058[5] = delta_x[5] + nom_x[5];
   out_3365569118000208058[6] = delta_x[6] + nom_x[6];
   out_3365569118000208058[7] = delta_x[7] + nom_x[7];
   out_3365569118000208058[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_5380110975370610231) {
   out_5380110975370610231[0] = -nom_x[0] + true_x[0];
   out_5380110975370610231[1] = -nom_x[1] + true_x[1];
   out_5380110975370610231[2] = -nom_x[2] + true_x[2];
   out_5380110975370610231[3] = -nom_x[3] + true_x[3];
   out_5380110975370610231[4] = -nom_x[4] + true_x[4];
   out_5380110975370610231[5] = -nom_x[5] + true_x[5];
   out_5380110975370610231[6] = -nom_x[6] + true_x[6];
   out_5380110975370610231[7] = -nom_x[7] + true_x[7];
   out_5380110975370610231[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_2504311089359476703) {
   out_2504311089359476703[0] = 1.0;
   out_2504311089359476703[1] = 0.0;
   out_2504311089359476703[2] = 0.0;
   out_2504311089359476703[3] = 0.0;
   out_2504311089359476703[4] = 0.0;
   out_2504311089359476703[5] = 0.0;
   out_2504311089359476703[6] = 0.0;
   out_2504311089359476703[7] = 0.0;
   out_2504311089359476703[8] = 0.0;
   out_2504311089359476703[9] = 0.0;
   out_2504311089359476703[10] = 1.0;
   out_2504311089359476703[11] = 0.0;
   out_2504311089359476703[12] = 0.0;
   out_2504311089359476703[13] = 0.0;
   out_2504311089359476703[14] = 0.0;
   out_2504311089359476703[15] = 0.0;
   out_2504311089359476703[16] = 0.0;
   out_2504311089359476703[17] = 0.0;
   out_2504311089359476703[18] = 0.0;
   out_2504311089359476703[19] = 0.0;
   out_2504311089359476703[20] = 1.0;
   out_2504311089359476703[21] = 0.0;
   out_2504311089359476703[22] = 0.0;
   out_2504311089359476703[23] = 0.0;
   out_2504311089359476703[24] = 0.0;
   out_2504311089359476703[25] = 0.0;
   out_2504311089359476703[26] = 0.0;
   out_2504311089359476703[27] = 0.0;
   out_2504311089359476703[28] = 0.0;
   out_2504311089359476703[29] = 0.0;
   out_2504311089359476703[30] = 1.0;
   out_2504311089359476703[31] = 0.0;
   out_2504311089359476703[32] = 0.0;
   out_2504311089359476703[33] = 0.0;
   out_2504311089359476703[34] = 0.0;
   out_2504311089359476703[35] = 0.0;
   out_2504311089359476703[36] = 0.0;
   out_2504311089359476703[37] = 0.0;
   out_2504311089359476703[38] = 0.0;
   out_2504311089359476703[39] = 0.0;
   out_2504311089359476703[40] = 1.0;
   out_2504311089359476703[41] = 0.0;
   out_2504311089359476703[42] = 0.0;
   out_2504311089359476703[43] = 0.0;
   out_2504311089359476703[44] = 0.0;
   out_2504311089359476703[45] = 0.0;
   out_2504311089359476703[46] = 0.0;
   out_2504311089359476703[47] = 0.0;
   out_2504311089359476703[48] = 0.0;
   out_2504311089359476703[49] = 0.0;
   out_2504311089359476703[50] = 1.0;
   out_2504311089359476703[51] = 0.0;
   out_2504311089359476703[52] = 0.0;
   out_2504311089359476703[53] = 0.0;
   out_2504311089359476703[54] = 0.0;
   out_2504311089359476703[55] = 0.0;
   out_2504311089359476703[56] = 0.0;
   out_2504311089359476703[57] = 0.0;
   out_2504311089359476703[58] = 0.0;
   out_2504311089359476703[59] = 0.0;
   out_2504311089359476703[60] = 1.0;
   out_2504311089359476703[61] = 0.0;
   out_2504311089359476703[62] = 0.0;
   out_2504311089359476703[63] = 0.0;
   out_2504311089359476703[64] = 0.0;
   out_2504311089359476703[65] = 0.0;
   out_2504311089359476703[66] = 0.0;
   out_2504311089359476703[67] = 0.0;
   out_2504311089359476703[68] = 0.0;
   out_2504311089359476703[69] = 0.0;
   out_2504311089359476703[70] = 1.0;
   out_2504311089359476703[71] = 0.0;
   out_2504311089359476703[72] = 0.0;
   out_2504311089359476703[73] = 0.0;
   out_2504311089359476703[74] = 0.0;
   out_2504311089359476703[75] = 0.0;
   out_2504311089359476703[76] = 0.0;
   out_2504311089359476703[77] = 0.0;
   out_2504311089359476703[78] = 0.0;
   out_2504311089359476703[79] = 0.0;
   out_2504311089359476703[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_2113948687906359301) {
   out_2113948687906359301[0] = state[0];
   out_2113948687906359301[1] = state[1];
   out_2113948687906359301[2] = state[2];
   out_2113948687906359301[3] = state[3];
   out_2113948687906359301[4] = state[4];
   out_2113948687906359301[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_2113948687906359301[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_2113948687906359301[7] = state[7];
   out_2113948687906359301[8] = state[8];
}
void F_fun(double *state, double dt, double *out_206720746751575203) {
   out_206720746751575203[0] = 1;
   out_206720746751575203[1] = 0;
   out_206720746751575203[2] = 0;
   out_206720746751575203[3] = 0;
   out_206720746751575203[4] = 0;
   out_206720746751575203[5] = 0;
   out_206720746751575203[6] = 0;
   out_206720746751575203[7] = 0;
   out_206720746751575203[8] = 0;
   out_206720746751575203[9] = 0;
   out_206720746751575203[10] = 1;
   out_206720746751575203[11] = 0;
   out_206720746751575203[12] = 0;
   out_206720746751575203[13] = 0;
   out_206720746751575203[14] = 0;
   out_206720746751575203[15] = 0;
   out_206720746751575203[16] = 0;
   out_206720746751575203[17] = 0;
   out_206720746751575203[18] = 0;
   out_206720746751575203[19] = 0;
   out_206720746751575203[20] = 1;
   out_206720746751575203[21] = 0;
   out_206720746751575203[22] = 0;
   out_206720746751575203[23] = 0;
   out_206720746751575203[24] = 0;
   out_206720746751575203[25] = 0;
   out_206720746751575203[26] = 0;
   out_206720746751575203[27] = 0;
   out_206720746751575203[28] = 0;
   out_206720746751575203[29] = 0;
   out_206720746751575203[30] = 1;
   out_206720746751575203[31] = 0;
   out_206720746751575203[32] = 0;
   out_206720746751575203[33] = 0;
   out_206720746751575203[34] = 0;
   out_206720746751575203[35] = 0;
   out_206720746751575203[36] = 0;
   out_206720746751575203[37] = 0;
   out_206720746751575203[38] = 0;
   out_206720746751575203[39] = 0;
   out_206720746751575203[40] = 1;
   out_206720746751575203[41] = 0;
   out_206720746751575203[42] = 0;
   out_206720746751575203[43] = 0;
   out_206720746751575203[44] = 0;
   out_206720746751575203[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_206720746751575203[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_206720746751575203[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_206720746751575203[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_206720746751575203[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_206720746751575203[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_206720746751575203[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_206720746751575203[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_206720746751575203[53] = -9.8100000000000005*dt;
   out_206720746751575203[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_206720746751575203[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_206720746751575203[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_206720746751575203[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_206720746751575203[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_206720746751575203[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_206720746751575203[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_206720746751575203[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_206720746751575203[62] = 0;
   out_206720746751575203[63] = 0;
   out_206720746751575203[64] = 0;
   out_206720746751575203[65] = 0;
   out_206720746751575203[66] = 0;
   out_206720746751575203[67] = 0;
   out_206720746751575203[68] = 0;
   out_206720746751575203[69] = 0;
   out_206720746751575203[70] = 1;
   out_206720746751575203[71] = 0;
   out_206720746751575203[72] = 0;
   out_206720746751575203[73] = 0;
   out_206720746751575203[74] = 0;
   out_206720746751575203[75] = 0;
   out_206720746751575203[76] = 0;
   out_206720746751575203[77] = 0;
   out_206720746751575203[78] = 0;
   out_206720746751575203[79] = 0;
   out_206720746751575203[80] = 1;
}
void h_25(double *state, double *unused, double *out_4746524988464866507) {
   out_4746524988464866507[0] = state[6];
}
void H_25(double *state, double *unused, double *out_9001334049249506654) {
   out_9001334049249506654[0] = 0;
   out_9001334049249506654[1] = 0;
   out_9001334049249506654[2] = 0;
   out_9001334049249506654[3] = 0;
   out_9001334049249506654[4] = 0;
   out_9001334049249506654[5] = 0;
   out_9001334049249506654[6] = 1;
   out_9001334049249506654[7] = 0;
   out_9001334049249506654[8] = 0;
}
void h_24(double *state, double *unused, double *out_2794460991545559300) {
   out_2794460991545559300[0] = state[4];
   out_2794460991545559300[1] = state[5];
}
void H_24(double *state, double *unused, double *out_3727839766336494060) {
   out_3727839766336494060[0] = 0;
   out_3727839766336494060[1] = 0;
   out_3727839766336494060[2] = 0;
   out_3727839766336494060[3] = 0;
   out_3727839766336494060[4] = 1;
   out_3727839766336494060[5] = 0;
   out_3727839766336494060[6] = 0;
   out_3727839766336494060[7] = 0;
   out_3727839766336494060[8] = 0;
   out_3727839766336494060[9] = 0;
   out_3727839766336494060[10] = 0;
   out_3727839766336494060[11] = 0;
   out_3727839766336494060[12] = 0;
   out_3727839766336494060[13] = 0;
   out_3727839766336494060[14] = 1;
   out_3727839766336494060[15] = 0;
   out_3727839766336494060[16] = 0;
   out_3727839766336494060[17] = 0;
}
void h_30(double *state, double *unused, double *out_2714033775784021818) {
   out_2714033775784021818[0] = state[4];
}
void H_30(double *state, double *unused, double *out_4917713694332436764) {
   out_4917713694332436764[0] = 0;
   out_4917713694332436764[1] = 0;
   out_4917713694332436764[2] = 0;
   out_4917713694332436764[3] = 0;
   out_4917713694332436764[4] = 1;
   out_4917713694332436764[5] = 0;
   out_4917713694332436764[6] = 0;
   out_4917713694332436764[7] = 0;
   out_4917713694332436764[8] = 0;
}
void h_26(double *state, double *unused, double *out_7715707043444867463) {
   out_7715707043444867463[0] = state[7];
}
void H_26(double *state, double *unused, double *out_5703906705585988738) {
   out_5703906705585988738[0] = 0;
   out_5703906705585988738[1] = 0;
   out_5703906705585988738[2] = 0;
   out_5703906705585988738[3] = 0;
   out_5703906705585988738[4] = 0;
   out_5703906705585988738[5] = 0;
   out_5703906705585988738[6] = 0;
   out_5703906705585988738[7] = 1;
   out_5703906705585988738[8] = 0;
}
void h_27(double *state, double *unused, double *out_1509299733494180747) {
   out_1509299733494180747[0] = state[3];
}
void H_27(double *state, double *unused, double *out_2742950382532011853) {
   out_2742950382532011853[0] = 0;
   out_2742950382532011853[1] = 0;
   out_2742950382532011853[2] = 0;
   out_2742950382532011853[3] = 1;
   out_2742950382532011853[4] = 0;
   out_2742950382532011853[5] = 0;
   out_2742950382532011853[6] = 0;
   out_2742950382532011853[7] = 0;
   out_2742950382532011853[8] = 0;
}
void h_29(double *state, double *unused, double *out_2110717891107544301) {
   out_2110717891107544301[0] = state[1];
}
void H_29(double *state, double *unused, double *out_5427945038646828948) {
   out_5427945038646828948[0] = 0;
   out_5427945038646828948[1] = 1;
   out_5427945038646828948[2] = 0;
   out_5427945038646828948[3] = 0;
   out_5427945038646828948[4] = 0;
   out_5427945038646828948[5] = 0;
   out_5427945038646828948[6] = 0;
   out_5427945038646828948[7] = 0;
   out_5427945038646828948[8] = 0;
}
void h_28(double *state, double *unused, double *out_2596026381850645074) {
   out_2596026381850645074[0] = state[0];
}
void H_28(double *state, double *unused, double *out_345546021577298374) {
   out_345546021577298374[0] = 1;
   out_345546021577298374[1] = 0;
   out_345546021577298374[2] = 0;
   out_345546021577298374[3] = 0;
   out_345546021577298374[4] = 0;
   out_345546021577298374[5] = 0;
   out_345546021577298374[6] = 0;
   out_345546021577298374[7] = 0;
   out_345546021577298374[8] = 0;
}
void h_31(double *state, double *unused, double *out_4903711656815995652) {
   out_4903711656815995652[0] = state[8];
}
void H_31(double *state, double *unused, double *out_5077698603352637262) {
   out_5077698603352637262[0] = 0;
   out_5077698603352637262[1] = 0;
   out_5077698603352637262[2] = 0;
   out_5077698603352637262[3] = 0;
   out_5077698603352637262[4] = 0;
   out_5077698603352637262[5] = 0;
   out_5077698603352637262[6] = 0;
   out_5077698603352637262[7] = 0;
   out_5077698603352637262[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_3365569118000208058) {
  err_fun(nom_x, delta_x, out_3365569118000208058);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_5380110975370610231) {
  inv_err_fun(nom_x, true_x, out_5380110975370610231);
}
void car_H_mod_fun(double *state, double *out_2504311089359476703) {
  H_mod_fun(state, out_2504311089359476703);
}
void car_f_fun(double *state, double dt, double *out_2113948687906359301) {
  f_fun(state,  dt, out_2113948687906359301);
}
void car_F_fun(double *state, double dt, double *out_206720746751575203) {
  F_fun(state,  dt, out_206720746751575203);
}
void car_h_25(double *state, double *unused, double *out_4746524988464866507) {
  h_25(state, unused, out_4746524988464866507);
}
void car_H_25(double *state, double *unused, double *out_9001334049249506654) {
  H_25(state, unused, out_9001334049249506654);
}
void car_h_24(double *state, double *unused, double *out_2794460991545559300) {
  h_24(state, unused, out_2794460991545559300);
}
void car_H_24(double *state, double *unused, double *out_3727839766336494060) {
  H_24(state, unused, out_3727839766336494060);
}
void car_h_30(double *state, double *unused, double *out_2714033775784021818) {
  h_30(state, unused, out_2714033775784021818);
}
void car_H_30(double *state, double *unused, double *out_4917713694332436764) {
  H_30(state, unused, out_4917713694332436764);
}
void car_h_26(double *state, double *unused, double *out_7715707043444867463) {
  h_26(state, unused, out_7715707043444867463);
}
void car_H_26(double *state, double *unused, double *out_5703906705585988738) {
  H_26(state, unused, out_5703906705585988738);
}
void car_h_27(double *state, double *unused, double *out_1509299733494180747) {
  h_27(state, unused, out_1509299733494180747);
}
void car_H_27(double *state, double *unused, double *out_2742950382532011853) {
  H_27(state, unused, out_2742950382532011853);
}
void car_h_29(double *state, double *unused, double *out_2110717891107544301) {
  h_29(state, unused, out_2110717891107544301);
}
void car_H_29(double *state, double *unused, double *out_5427945038646828948) {
  H_29(state, unused, out_5427945038646828948);
}
void car_h_28(double *state, double *unused, double *out_2596026381850645074) {
  h_28(state, unused, out_2596026381850645074);
}
void car_H_28(double *state, double *unused, double *out_345546021577298374) {
  H_28(state, unused, out_345546021577298374);
}
void car_h_31(double *state, double *unused, double *out_4903711656815995652) {
  h_31(state, unused, out_4903711656815995652);
}
void car_H_31(double *state, double *unused, double *out_5077698603352637262) {
  H_31(state, unused, out_5077698603352637262);
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
