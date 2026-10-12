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
void err_fun(double *nom_x, double *delta_x, double *out_8771745385019272911) {
   out_8771745385019272911[0] = delta_x[0] + nom_x[0];
   out_8771745385019272911[1] = delta_x[1] + nom_x[1];
   out_8771745385019272911[2] = delta_x[2] + nom_x[2];
   out_8771745385019272911[3] = delta_x[3] + nom_x[3];
   out_8771745385019272911[4] = delta_x[4] + nom_x[4];
   out_8771745385019272911[5] = delta_x[5] + nom_x[5];
   out_8771745385019272911[6] = delta_x[6] + nom_x[6];
   out_8771745385019272911[7] = delta_x[7] + nom_x[7];
   out_8771745385019272911[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_3231363094273967832) {
   out_3231363094273967832[0] = -nom_x[0] + true_x[0];
   out_3231363094273967832[1] = -nom_x[1] + true_x[1];
   out_3231363094273967832[2] = -nom_x[2] + true_x[2];
   out_3231363094273967832[3] = -nom_x[3] + true_x[3];
   out_3231363094273967832[4] = -nom_x[4] + true_x[4];
   out_3231363094273967832[5] = -nom_x[5] + true_x[5];
   out_3231363094273967832[6] = -nom_x[6] + true_x[6];
   out_3231363094273967832[7] = -nom_x[7] + true_x[7];
   out_3231363094273967832[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_5279329364050306118) {
   out_5279329364050306118[0] = 1.0;
   out_5279329364050306118[1] = 0.0;
   out_5279329364050306118[2] = 0.0;
   out_5279329364050306118[3] = 0.0;
   out_5279329364050306118[4] = 0.0;
   out_5279329364050306118[5] = 0.0;
   out_5279329364050306118[6] = 0.0;
   out_5279329364050306118[7] = 0.0;
   out_5279329364050306118[8] = 0.0;
   out_5279329364050306118[9] = 0.0;
   out_5279329364050306118[10] = 1.0;
   out_5279329364050306118[11] = 0.0;
   out_5279329364050306118[12] = 0.0;
   out_5279329364050306118[13] = 0.0;
   out_5279329364050306118[14] = 0.0;
   out_5279329364050306118[15] = 0.0;
   out_5279329364050306118[16] = 0.0;
   out_5279329364050306118[17] = 0.0;
   out_5279329364050306118[18] = 0.0;
   out_5279329364050306118[19] = 0.0;
   out_5279329364050306118[20] = 1.0;
   out_5279329364050306118[21] = 0.0;
   out_5279329364050306118[22] = 0.0;
   out_5279329364050306118[23] = 0.0;
   out_5279329364050306118[24] = 0.0;
   out_5279329364050306118[25] = 0.0;
   out_5279329364050306118[26] = 0.0;
   out_5279329364050306118[27] = 0.0;
   out_5279329364050306118[28] = 0.0;
   out_5279329364050306118[29] = 0.0;
   out_5279329364050306118[30] = 1.0;
   out_5279329364050306118[31] = 0.0;
   out_5279329364050306118[32] = 0.0;
   out_5279329364050306118[33] = 0.0;
   out_5279329364050306118[34] = 0.0;
   out_5279329364050306118[35] = 0.0;
   out_5279329364050306118[36] = 0.0;
   out_5279329364050306118[37] = 0.0;
   out_5279329364050306118[38] = 0.0;
   out_5279329364050306118[39] = 0.0;
   out_5279329364050306118[40] = 1.0;
   out_5279329364050306118[41] = 0.0;
   out_5279329364050306118[42] = 0.0;
   out_5279329364050306118[43] = 0.0;
   out_5279329364050306118[44] = 0.0;
   out_5279329364050306118[45] = 0.0;
   out_5279329364050306118[46] = 0.0;
   out_5279329364050306118[47] = 0.0;
   out_5279329364050306118[48] = 0.0;
   out_5279329364050306118[49] = 0.0;
   out_5279329364050306118[50] = 1.0;
   out_5279329364050306118[51] = 0.0;
   out_5279329364050306118[52] = 0.0;
   out_5279329364050306118[53] = 0.0;
   out_5279329364050306118[54] = 0.0;
   out_5279329364050306118[55] = 0.0;
   out_5279329364050306118[56] = 0.0;
   out_5279329364050306118[57] = 0.0;
   out_5279329364050306118[58] = 0.0;
   out_5279329364050306118[59] = 0.0;
   out_5279329364050306118[60] = 1.0;
   out_5279329364050306118[61] = 0.0;
   out_5279329364050306118[62] = 0.0;
   out_5279329364050306118[63] = 0.0;
   out_5279329364050306118[64] = 0.0;
   out_5279329364050306118[65] = 0.0;
   out_5279329364050306118[66] = 0.0;
   out_5279329364050306118[67] = 0.0;
   out_5279329364050306118[68] = 0.0;
   out_5279329364050306118[69] = 0.0;
   out_5279329364050306118[70] = 1.0;
   out_5279329364050306118[71] = 0.0;
   out_5279329364050306118[72] = 0.0;
   out_5279329364050306118[73] = 0.0;
   out_5279329364050306118[74] = 0.0;
   out_5279329364050306118[75] = 0.0;
   out_5279329364050306118[76] = 0.0;
   out_5279329364050306118[77] = 0.0;
   out_5279329364050306118[78] = 0.0;
   out_5279329364050306118[79] = 0.0;
   out_5279329364050306118[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_9065464123133416094) {
   out_9065464123133416094[0] = state[0];
   out_9065464123133416094[1] = state[1];
   out_9065464123133416094[2] = state[2];
   out_9065464123133416094[3] = state[3];
   out_9065464123133416094[4] = state[4];
   out_9065464123133416094[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_9065464123133416094[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_9065464123133416094[7] = state[7];
   out_9065464123133416094[8] = state[8];
}
void F_fun(double *state, double dt, double *out_4008021677178468012) {
   out_4008021677178468012[0] = 1;
   out_4008021677178468012[1] = 0;
   out_4008021677178468012[2] = 0;
   out_4008021677178468012[3] = 0;
   out_4008021677178468012[4] = 0;
   out_4008021677178468012[5] = 0;
   out_4008021677178468012[6] = 0;
   out_4008021677178468012[7] = 0;
   out_4008021677178468012[8] = 0;
   out_4008021677178468012[9] = 0;
   out_4008021677178468012[10] = 1;
   out_4008021677178468012[11] = 0;
   out_4008021677178468012[12] = 0;
   out_4008021677178468012[13] = 0;
   out_4008021677178468012[14] = 0;
   out_4008021677178468012[15] = 0;
   out_4008021677178468012[16] = 0;
   out_4008021677178468012[17] = 0;
   out_4008021677178468012[18] = 0;
   out_4008021677178468012[19] = 0;
   out_4008021677178468012[20] = 1;
   out_4008021677178468012[21] = 0;
   out_4008021677178468012[22] = 0;
   out_4008021677178468012[23] = 0;
   out_4008021677178468012[24] = 0;
   out_4008021677178468012[25] = 0;
   out_4008021677178468012[26] = 0;
   out_4008021677178468012[27] = 0;
   out_4008021677178468012[28] = 0;
   out_4008021677178468012[29] = 0;
   out_4008021677178468012[30] = 1;
   out_4008021677178468012[31] = 0;
   out_4008021677178468012[32] = 0;
   out_4008021677178468012[33] = 0;
   out_4008021677178468012[34] = 0;
   out_4008021677178468012[35] = 0;
   out_4008021677178468012[36] = 0;
   out_4008021677178468012[37] = 0;
   out_4008021677178468012[38] = 0;
   out_4008021677178468012[39] = 0;
   out_4008021677178468012[40] = 1;
   out_4008021677178468012[41] = 0;
   out_4008021677178468012[42] = 0;
   out_4008021677178468012[43] = 0;
   out_4008021677178468012[44] = 0;
   out_4008021677178468012[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_4008021677178468012[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_4008021677178468012[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_4008021677178468012[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_4008021677178468012[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_4008021677178468012[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_4008021677178468012[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_4008021677178468012[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_4008021677178468012[53] = -9.8100000000000005*dt;
   out_4008021677178468012[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_4008021677178468012[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_4008021677178468012[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4008021677178468012[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4008021677178468012[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_4008021677178468012[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_4008021677178468012[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_4008021677178468012[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_4008021677178468012[62] = 0;
   out_4008021677178468012[63] = 0;
   out_4008021677178468012[64] = 0;
   out_4008021677178468012[65] = 0;
   out_4008021677178468012[66] = 0;
   out_4008021677178468012[67] = 0;
   out_4008021677178468012[68] = 0;
   out_4008021677178468012[69] = 0;
   out_4008021677178468012[70] = 1;
   out_4008021677178468012[71] = 0;
   out_4008021677178468012[72] = 0;
   out_4008021677178468012[73] = 0;
   out_4008021677178468012[74] = 0;
   out_4008021677178468012[75] = 0;
   out_4008021677178468012[76] = 0;
   out_4008021677178468012[77] = 0;
   out_4008021677178468012[78] = 0;
   out_4008021677178468012[79] = 0;
   out_4008021677178468012[80] = 1;
}
void h_25(double *state, double *unused, double *out_5404965656887369328) {
   out_5404965656887369328[0] = state[6];
}
void H_25(double *state, double *unused, double *out_5246076676685385693) {
   out_5246076676685385693[0] = 0;
   out_5246076676685385693[1] = 0;
   out_5246076676685385693[2] = 0;
   out_5246076676685385693[3] = 0;
   out_5246076676685385693[4] = 0;
   out_5246076676685385693[5] = 0;
   out_5246076676685385693[6] = 1;
   out_5246076676685385693[7] = 0;
   out_5246076676685385693[8] = 0;
}
void h_24(double *state, double *unused, double *out_1243581068366124229) {
   out_1243581068366124229[0] = state[4];
   out_1243581068366124229[1] = state[5];
}
void H_24(double *state, double *unused, double *out_1688151077883062557) {
   out_1688151077883062557[0] = 0;
   out_1688151077883062557[1] = 0;
   out_1688151077883062557[2] = 0;
   out_1688151077883062557[3] = 0;
   out_1688151077883062557[4] = 1;
   out_1688151077883062557[5] = 0;
   out_1688151077883062557[6] = 0;
   out_1688151077883062557[7] = 0;
   out_1688151077883062557[8] = 0;
   out_1688151077883062557[9] = 0;
   out_1688151077883062557[10] = 0;
   out_1688151077883062557[11] = 0;
   out_1688151077883062557[12] = 0;
   out_1688151077883062557[13] = 0;
   out_1688151077883062557[14] = 1;
   out_1688151077883062557[15] = 0;
   out_1688151077883062557[16] = 0;
   out_1688151077883062557[17] = 0;
}
void h_30(double *state, double *unused, double *out_4545117735558442296) {
   out_4545117735558442296[0] = state[4];
}
void H_30(double *state, double *unused, double *out_8672971066896557725) {
   out_8672971066896557725[0] = 0;
   out_8672971066896557725[1] = 0;
   out_8672971066896557725[2] = 0;
   out_8672971066896557725[3] = 0;
   out_8672971066896557725[4] = 1;
   out_8672971066896557725[5] = 0;
   out_8672971066896557725[6] = 0;
   out_8672971066896557725[7] = 0;
   out_8672971066896557725[8] = 0;
}
void h_26(double *state, double *unused, double *out_456555532102403349) {
   out_456555532102403349[0] = state[7];
}
void H_26(double *state, double *unused, double *out_8987579995559441917) {
   out_8987579995559441917[0] = 0;
   out_8987579995559441917[1] = 0;
   out_8987579995559441917[2] = 0;
   out_8987579995559441917[3] = 0;
   out_8987579995559441917[4] = 0;
   out_8987579995559441917[5] = 0;
   out_8987579995559441917[6] = 0;
   out_8987579995559441917[7] = 1;
   out_8987579995559441917[8] = 0;
}
void h_27(double *state, double *unused, double *out_338548138169026605) {
   out_338548138169026605[0] = state[3];
}
void H_27(double *state, double *unused, double *out_6498207755096132814) {
   out_6498207755096132814[0] = 0;
   out_6498207755096132814[1] = 0;
   out_6498207755096132814[2] = 0;
   out_6498207755096132814[3] = 1;
   out_6498207755096132814[4] = 0;
   out_6498207755096132814[5] = 0;
   out_6498207755096132814[6] = 0;
   out_6498207755096132814[7] = 0;
   out_6498207755096132814[8] = 0;
}
void h_29(double *state, double *unused, double *out_3601607882656779861) {
   out_3601607882656779861[0] = state[1];
}
void H_29(double *state, double *unused, double *out_9183202411210949909) {
   out_9183202411210949909[0] = 0;
   out_9183202411210949909[1] = 1;
   out_9183202411210949909[2] = 0;
   out_9183202411210949909[3] = 0;
   out_9183202411210949909[4] = 0;
   out_9183202411210949909[5] = 0;
   out_9183202411210949909[6] = 0;
   out_9183202411210949909[7] = 0;
   out_9183202411210949909[8] = 0;
}
void h_28(double *state, double *unused, double *out_8457761326096970535) {
   out_8457761326096970535[0] = state[0];
}
void H_28(double *state, double *unused, double *out_4100803394141419335) {
   out_4100803394141419335[0] = 1;
   out_4100803394141419335[1] = 0;
   out_4100803394141419335[2] = 0;
   out_4100803394141419335[3] = 0;
   out_4100803394141419335[4] = 0;
   out_4100803394141419335[5] = 0;
   out_4100803394141419335[6] = 0;
   out_4100803394141419335[7] = 0;
   out_4100803394141419335[8] = 0;
}
void h_31(double *state, double *unused, double *out_1509086364917783500) {
   out_1509086364917783500[0] = state[8];
}
void H_31(double *state, double *unused, double *out_8832955975916758223) {
   out_8832955975916758223[0] = 0;
   out_8832955975916758223[1] = 0;
   out_8832955975916758223[2] = 0;
   out_8832955975916758223[3] = 0;
   out_8832955975916758223[4] = 0;
   out_8832955975916758223[5] = 0;
   out_8832955975916758223[6] = 0;
   out_8832955975916758223[7] = 0;
   out_8832955975916758223[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_8771745385019272911) {
  err_fun(nom_x, delta_x, out_8771745385019272911);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_3231363094273967832) {
  inv_err_fun(nom_x, true_x, out_3231363094273967832);
}
void car_H_mod_fun(double *state, double *out_5279329364050306118) {
  H_mod_fun(state, out_5279329364050306118);
}
void car_f_fun(double *state, double dt, double *out_9065464123133416094) {
  f_fun(state,  dt, out_9065464123133416094);
}
void car_F_fun(double *state, double dt, double *out_4008021677178468012) {
  F_fun(state,  dt, out_4008021677178468012);
}
void car_h_25(double *state, double *unused, double *out_5404965656887369328) {
  h_25(state, unused, out_5404965656887369328);
}
void car_H_25(double *state, double *unused, double *out_5246076676685385693) {
  H_25(state, unused, out_5246076676685385693);
}
void car_h_24(double *state, double *unused, double *out_1243581068366124229) {
  h_24(state, unused, out_1243581068366124229);
}
void car_H_24(double *state, double *unused, double *out_1688151077883062557) {
  H_24(state, unused, out_1688151077883062557);
}
void car_h_30(double *state, double *unused, double *out_4545117735558442296) {
  h_30(state, unused, out_4545117735558442296);
}
void car_H_30(double *state, double *unused, double *out_8672971066896557725) {
  H_30(state, unused, out_8672971066896557725);
}
void car_h_26(double *state, double *unused, double *out_456555532102403349) {
  h_26(state, unused, out_456555532102403349);
}
void car_H_26(double *state, double *unused, double *out_8987579995559441917) {
  H_26(state, unused, out_8987579995559441917);
}
void car_h_27(double *state, double *unused, double *out_338548138169026605) {
  h_27(state, unused, out_338548138169026605);
}
void car_H_27(double *state, double *unused, double *out_6498207755096132814) {
  H_27(state, unused, out_6498207755096132814);
}
void car_h_29(double *state, double *unused, double *out_3601607882656779861) {
  h_29(state, unused, out_3601607882656779861);
}
void car_H_29(double *state, double *unused, double *out_9183202411210949909) {
  H_29(state, unused, out_9183202411210949909);
}
void car_h_28(double *state, double *unused, double *out_8457761326096970535) {
  h_28(state, unused, out_8457761326096970535);
}
void car_H_28(double *state, double *unused, double *out_4100803394141419335) {
  H_28(state, unused, out_4100803394141419335);
}
void car_h_31(double *state, double *unused, double *out_1509086364917783500) {
  h_31(state, unused, out_1509086364917783500);
}
void car_H_31(double *state, double *unused, double *out_8832955975916758223) {
  H_31(state, unused, out_8832955975916758223);
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
