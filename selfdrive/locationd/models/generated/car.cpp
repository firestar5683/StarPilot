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
void err_fun(double *nom_x, double *delta_x, double *out_789804740016769707) {
   out_789804740016769707[0] = delta_x[0] + nom_x[0];
   out_789804740016769707[1] = delta_x[1] + nom_x[1];
   out_789804740016769707[2] = delta_x[2] + nom_x[2];
   out_789804740016769707[3] = delta_x[3] + nom_x[3];
   out_789804740016769707[4] = delta_x[4] + nom_x[4];
   out_789804740016769707[5] = delta_x[5] + nom_x[5];
   out_789804740016769707[6] = delta_x[6] + nom_x[6];
   out_789804740016769707[7] = delta_x[7] + nom_x[7];
   out_789804740016769707[8] = delta_x[8] + nom_x[8];
}
void inv_err_fun(double *nom_x, double *true_x, double *out_385986033898548509) {
   out_385986033898548509[0] = -nom_x[0] + true_x[0];
   out_385986033898548509[1] = -nom_x[1] + true_x[1];
   out_385986033898548509[2] = -nom_x[2] + true_x[2];
   out_385986033898548509[3] = -nom_x[3] + true_x[3];
   out_385986033898548509[4] = -nom_x[4] + true_x[4];
   out_385986033898548509[5] = -nom_x[5] + true_x[5];
   out_385986033898548509[6] = -nom_x[6] + true_x[6];
   out_385986033898548509[7] = -nom_x[7] + true_x[7];
   out_385986033898548509[8] = -nom_x[8] + true_x[8];
}
void H_mod_fun(double *state, double *out_4046004184415297016) {
   out_4046004184415297016[0] = 1.0;
   out_4046004184415297016[1] = 0.0;
   out_4046004184415297016[2] = 0.0;
   out_4046004184415297016[3] = 0.0;
   out_4046004184415297016[4] = 0.0;
   out_4046004184415297016[5] = 0.0;
   out_4046004184415297016[6] = 0.0;
   out_4046004184415297016[7] = 0.0;
   out_4046004184415297016[8] = 0.0;
   out_4046004184415297016[9] = 0.0;
   out_4046004184415297016[10] = 1.0;
   out_4046004184415297016[11] = 0.0;
   out_4046004184415297016[12] = 0.0;
   out_4046004184415297016[13] = 0.0;
   out_4046004184415297016[14] = 0.0;
   out_4046004184415297016[15] = 0.0;
   out_4046004184415297016[16] = 0.0;
   out_4046004184415297016[17] = 0.0;
   out_4046004184415297016[18] = 0.0;
   out_4046004184415297016[19] = 0.0;
   out_4046004184415297016[20] = 1.0;
   out_4046004184415297016[21] = 0.0;
   out_4046004184415297016[22] = 0.0;
   out_4046004184415297016[23] = 0.0;
   out_4046004184415297016[24] = 0.0;
   out_4046004184415297016[25] = 0.0;
   out_4046004184415297016[26] = 0.0;
   out_4046004184415297016[27] = 0.0;
   out_4046004184415297016[28] = 0.0;
   out_4046004184415297016[29] = 0.0;
   out_4046004184415297016[30] = 1.0;
   out_4046004184415297016[31] = 0.0;
   out_4046004184415297016[32] = 0.0;
   out_4046004184415297016[33] = 0.0;
   out_4046004184415297016[34] = 0.0;
   out_4046004184415297016[35] = 0.0;
   out_4046004184415297016[36] = 0.0;
   out_4046004184415297016[37] = 0.0;
   out_4046004184415297016[38] = 0.0;
   out_4046004184415297016[39] = 0.0;
   out_4046004184415297016[40] = 1.0;
   out_4046004184415297016[41] = 0.0;
   out_4046004184415297016[42] = 0.0;
   out_4046004184415297016[43] = 0.0;
   out_4046004184415297016[44] = 0.0;
   out_4046004184415297016[45] = 0.0;
   out_4046004184415297016[46] = 0.0;
   out_4046004184415297016[47] = 0.0;
   out_4046004184415297016[48] = 0.0;
   out_4046004184415297016[49] = 0.0;
   out_4046004184415297016[50] = 1.0;
   out_4046004184415297016[51] = 0.0;
   out_4046004184415297016[52] = 0.0;
   out_4046004184415297016[53] = 0.0;
   out_4046004184415297016[54] = 0.0;
   out_4046004184415297016[55] = 0.0;
   out_4046004184415297016[56] = 0.0;
   out_4046004184415297016[57] = 0.0;
   out_4046004184415297016[58] = 0.0;
   out_4046004184415297016[59] = 0.0;
   out_4046004184415297016[60] = 1.0;
   out_4046004184415297016[61] = 0.0;
   out_4046004184415297016[62] = 0.0;
   out_4046004184415297016[63] = 0.0;
   out_4046004184415297016[64] = 0.0;
   out_4046004184415297016[65] = 0.0;
   out_4046004184415297016[66] = 0.0;
   out_4046004184415297016[67] = 0.0;
   out_4046004184415297016[68] = 0.0;
   out_4046004184415297016[69] = 0.0;
   out_4046004184415297016[70] = 1.0;
   out_4046004184415297016[71] = 0.0;
   out_4046004184415297016[72] = 0.0;
   out_4046004184415297016[73] = 0.0;
   out_4046004184415297016[74] = 0.0;
   out_4046004184415297016[75] = 0.0;
   out_4046004184415297016[76] = 0.0;
   out_4046004184415297016[77] = 0.0;
   out_4046004184415297016[78] = 0.0;
   out_4046004184415297016[79] = 0.0;
   out_4046004184415297016[80] = 1.0;
}
void f_fun(double *state, double dt, double *out_467921565295650481) {
   out_467921565295650481[0] = state[0];
   out_467921565295650481[1] = state[1];
   out_467921565295650481[2] = state[2];
   out_467921565295650481[3] = state[3];
   out_467921565295650481[4] = state[4];
   out_467921565295650481[5] = dt*((-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]))*state[6] - 9.8100000000000005*state[8] + stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*state[1]) + (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*state[4])) + state[5];
   out_467921565295650481[6] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*state[4])) + state[6];
   out_467921565295650481[7] = state[7];
   out_467921565295650481[8] = state[8];
}
void F_fun(double *state, double dt, double *out_2429260194375294140) {
   out_2429260194375294140[0] = 1;
   out_2429260194375294140[1] = 0;
   out_2429260194375294140[2] = 0;
   out_2429260194375294140[3] = 0;
   out_2429260194375294140[4] = 0;
   out_2429260194375294140[5] = 0;
   out_2429260194375294140[6] = 0;
   out_2429260194375294140[7] = 0;
   out_2429260194375294140[8] = 0;
   out_2429260194375294140[9] = 0;
   out_2429260194375294140[10] = 1;
   out_2429260194375294140[11] = 0;
   out_2429260194375294140[12] = 0;
   out_2429260194375294140[13] = 0;
   out_2429260194375294140[14] = 0;
   out_2429260194375294140[15] = 0;
   out_2429260194375294140[16] = 0;
   out_2429260194375294140[17] = 0;
   out_2429260194375294140[18] = 0;
   out_2429260194375294140[19] = 0;
   out_2429260194375294140[20] = 1;
   out_2429260194375294140[21] = 0;
   out_2429260194375294140[22] = 0;
   out_2429260194375294140[23] = 0;
   out_2429260194375294140[24] = 0;
   out_2429260194375294140[25] = 0;
   out_2429260194375294140[26] = 0;
   out_2429260194375294140[27] = 0;
   out_2429260194375294140[28] = 0;
   out_2429260194375294140[29] = 0;
   out_2429260194375294140[30] = 1;
   out_2429260194375294140[31] = 0;
   out_2429260194375294140[32] = 0;
   out_2429260194375294140[33] = 0;
   out_2429260194375294140[34] = 0;
   out_2429260194375294140[35] = 0;
   out_2429260194375294140[36] = 0;
   out_2429260194375294140[37] = 0;
   out_2429260194375294140[38] = 0;
   out_2429260194375294140[39] = 0;
   out_2429260194375294140[40] = 1;
   out_2429260194375294140[41] = 0;
   out_2429260194375294140[42] = 0;
   out_2429260194375294140[43] = 0;
   out_2429260194375294140[44] = 0;
   out_2429260194375294140[45] = dt*(stiffness_front*(-state[2] - state[3] + state[7])/(mass*state[1]) + (-stiffness_front - stiffness_rear)*state[5]/(mass*state[4]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[6]/(mass*state[4]));
   out_2429260194375294140[46] = -dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(mass*pow(state[1], 2));
   out_2429260194375294140[47] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_2429260194375294140[48] = -dt*stiffness_front*state[0]/(mass*state[1]);
   out_2429260194375294140[49] = dt*((-1 - (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*pow(state[4], 2)))*state[6] - (-stiffness_front*state[0] - stiffness_rear*state[0])*state[5]/(mass*pow(state[4], 2)));
   out_2429260194375294140[50] = dt*(-stiffness_front*state[0] - stiffness_rear*state[0])/(mass*state[4]) + 1;
   out_2429260194375294140[51] = dt*(-state[4] + (-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(mass*state[4]));
   out_2429260194375294140[52] = dt*stiffness_front*state[0]/(mass*state[1]);
   out_2429260194375294140[53] = -9.8100000000000005*dt;
   out_2429260194375294140[54] = dt*(center_to_front*stiffness_front*(-state[2] - state[3] + state[7])/(rotational_inertia*state[1]) + (-center_to_front*stiffness_front + center_to_rear*stiffness_rear)*state[5]/(rotational_inertia*state[4]) + (-pow(center_to_front, 2)*stiffness_front - pow(center_to_rear, 2)*stiffness_rear)*state[6]/(rotational_inertia*state[4]));
   out_2429260194375294140[55] = -center_to_front*dt*stiffness_front*(-state[2] - state[3] + state[7])*state[0]/(rotational_inertia*pow(state[1], 2));
   out_2429260194375294140[56] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2429260194375294140[57] = -center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2429260194375294140[58] = dt*(-(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])*state[5]/(rotational_inertia*pow(state[4], 2)) - (-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])*state[6]/(rotational_inertia*pow(state[4], 2)));
   out_2429260194375294140[59] = dt*(-center_to_front*stiffness_front*state[0] + center_to_rear*stiffness_rear*state[0])/(rotational_inertia*state[4]);
   out_2429260194375294140[60] = dt*(-pow(center_to_front, 2)*stiffness_front*state[0] - pow(center_to_rear, 2)*stiffness_rear*state[0])/(rotational_inertia*state[4]) + 1;
   out_2429260194375294140[61] = center_to_front*dt*stiffness_front*state[0]/(rotational_inertia*state[1]);
   out_2429260194375294140[62] = 0;
   out_2429260194375294140[63] = 0;
   out_2429260194375294140[64] = 0;
   out_2429260194375294140[65] = 0;
   out_2429260194375294140[66] = 0;
   out_2429260194375294140[67] = 0;
   out_2429260194375294140[68] = 0;
   out_2429260194375294140[69] = 0;
   out_2429260194375294140[70] = 1;
   out_2429260194375294140[71] = 0;
   out_2429260194375294140[72] = 0;
   out_2429260194375294140[73] = 0;
   out_2429260194375294140[74] = 0;
   out_2429260194375294140[75] = 0;
   out_2429260194375294140[76] = 0;
   out_2429260194375294140[77] = 0;
   out_2429260194375294140[78] = 0;
   out_2429260194375294140[79] = 0;
   out_2429260194375294140[80] = 1;
}
void h_25(double *state, double *unused, double *out_4530459753918271082) {
   out_4530459753918271082[0] = state[6];
}
void H_25(double *state, double *unused, double *out_4551338626615593728) {
   out_4551338626615593728[0] = 0;
   out_4551338626615593728[1] = 0;
   out_4551338626615593728[2] = 0;
   out_4551338626615593728[3] = 0;
   out_4551338626615593728[4] = 0;
   out_4551338626615593728[5] = 0;
   out_4551338626615593728[6] = 1;
   out_4551338626615593728[7] = 0;
   out_4551338626615593728[8] = 0;
}
void h_24(double *state, double *unused, double *out_211848015086222289) {
   out_211848015086222289[0] = state[4];
   out_211848015086222289[1] = state[5];
}
void H_24(double *state, double *unused, double *out_7319833640502439787) {
   out_7319833640502439787[0] = 0;
   out_7319833640502439787[1] = 0;
   out_7319833640502439787[2] = 0;
   out_7319833640502439787[3] = 0;
   out_7319833640502439787[4] = 1;
   out_7319833640502439787[5] = 0;
   out_7319833640502439787[6] = 0;
   out_7319833640502439787[7] = 0;
   out_7319833640502439787[8] = 0;
   out_7319833640502439787[9] = 0;
   out_7319833640502439787[10] = 0;
   out_7319833640502439787[11] = 0;
   out_7319833640502439787[12] = 0;
   out_7319833640502439787[13] = 0;
   out_7319833640502439787[14] = 1;
   out_7319833640502439787[15] = 0;
   out_7319833640502439787[16] = 0;
   out_7319833640502439787[17] = 0;
}
void h_30(double *state, double *unused, double *out_4687646422269400227) {
   out_4687646422269400227[0] = state[4];
}
void H_30(double *state, double *unused, double *out_4421999679472353658) {
   out_4421999679472353658[0] = 0;
   out_4421999679472353658[1] = 0;
   out_4421999679472353658[2] = 0;
   out_4421999679472353658[3] = 0;
   out_4421999679472353658[4] = 1;
   out_4421999679472353658[5] = 0;
   out_4421999679472353658[6] = 0;
   out_4421999679472353658[7] = 0;
   out_4421999679472353658[8] = 0;
}
void h_26(double *state, double *unused, double *out_1875094318999546844) {
   out_1875094318999546844[0] = state[7];
}
void H_26(double *state, double *unused, double *out_809835307741537504) {
   out_809835307741537504[0] = 0;
   out_809835307741537504[1] = 0;
   out_809835307741537504[2] = 0;
   out_809835307741537504[3] = 0;
   out_809835307741537504[4] = 0;
   out_809835307741537504[5] = 0;
   out_809835307741537504[6] = 0;
   out_809835307741537504[7] = 1;
   out_809835307741537504[8] = 0;
}
void h_27(double *state, double *unused, double *out_8953904322109987302) {
   out_8953904322109987302[0] = state[3];
}
void H_27(double *state, double *unused, double *out_2247236367671928747) {
   out_2247236367671928747[0] = 0;
   out_2247236367671928747[1] = 0;
   out_2247236367671928747[2] = 0;
   out_2247236367671928747[3] = 1;
   out_2247236367671928747[4] = 0;
   out_2247236367671928747[5] = 0;
   out_2247236367671928747[6] = 0;
   out_2247236367671928747[7] = 0;
   out_2247236367671928747[8] = 0;
}
void h_29(double *state, double *unused, double *out_5855390223345541964) {
   out_5855390223345541964[0] = state[1];
}
void H_29(double *state, double *unused, double *out_4932231023786745842) {
   out_4932231023786745842[0] = 0;
   out_4932231023786745842[1] = 1;
   out_4932231023786745842[2] = 0;
   out_4932231023786745842[3] = 0;
   out_4932231023786745842[4] = 0;
   out_4932231023786745842[5] = 0;
   out_4932231023786745842[6] = 0;
   out_4932231023786745842[7] = 0;
   out_4932231023786745842[8] = 0;
}
void h_28(double *state, double *unused, double *out_8510755658264266202) {
   out_8510755658264266202[0] = state[0];
}
void H_28(double *state, double *unused, double *out_6895861295352072093) {
   out_6895861295352072093[0] = 1;
   out_6895861295352072093[1] = 0;
   out_6895861295352072093[2] = 0;
   out_6895861295352072093[3] = 0;
   out_6895861295352072093[4] = 0;
   out_6895861295352072093[5] = 0;
   out_6895861295352072093[6] = 0;
   out_6895861295352072093[7] = 0;
   out_6895861295352072093[8] = 0;
}
void h_31(double *state, double *unused, double *out_3677036992164635768) {
   out_3677036992164635768[0] = state[8];
}
void H_31(double *state, double *unused, double *out_4581984588492554156) {
   out_4581984588492554156[0] = 0;
   out_4581984588492554156[1] = 0;
   out_4581984588492554156[2] = 0;
   out_4581984588492554156[3] = 0;
   out_4581984588492554156[4] = 0;
   out_4581984588492554156[5] = 0;
   out_4581984588492554156[6] = 0;
   out_4581984588492554156[7] = 0;
   out_4581984588492554156[8] = 1;
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
void car_err_fun(double *nom_x, double *delta_x, double *out_789804740016769707) {
  err_fun(nom_x, delta_x, out_789804740016769707);
}
void car_inv_err_fun(double *nom_x, double *true_x, double *out_385986033898548509) {
  inv_err_fun(nom_x, true_x, out_385986033898548509);
}
void car_H_mod_fun(double *state, double *out_4046004184415297016) {
  H_mod_fun(state, out_4046004184415297016);
}
void car_f_fun(double *state, double dt, double *out_467921565295650481) {
  f_fun(state,  dt, out_467921565295650481);
}
void car_F_fun(double *state, double dt, double *out_2429260194375294140) {
  F_fun(state,  dt, out_2429260194375294140);
}
void car_h_25(double *state, double *unused, double *out_4530459753918271082) {
  h_25(state, unused, out_4530459753918271082);
}
void car_H_25(double *state, double *unused, double *out_4551338626615593728) {
  H_25(state, unused, out_4551338626615593728);
}
void car_h_24(double *state, double *unused, double *out_211848015086222289) {
  h_24(state, unused, out_211848015086222289);
}
void car_H_24(double *state, double *unused, double *out_7319833640502439787) {
  H_24(state, unused, out_7319833640502439787);
}
void car_h_30(double *state, double *unused, double *out_4687646422269400227) {
  h_30(state, unused, out_4687646422269400227);
}
void car_H_30(double *state, double *unused, double *out_4421999679472353658) {
  H_30(state, unused, out_4421999679472353658);
}
void car_h_26(double *state, double *unused, double *out_1875094318999546844) {
  h_26(state, unused, out_1875094318999546844);
}
void car_H_26(double *state, double *unused, double *out_809835307741537504) {
  H_26(state, unused, out_809835307741537504);
}
void car_h_27(double *state, double *unused, double *out_8953904322109987302) {
  h_27(state, unused, out_8953904322109987302);
}
void car_H_27(double *state, double *unused, double *out_2247236367671928747) {
  H_27(state, unused, out_2247236367671928747);
}
void car_h_29(double *state, double *unused, double *out_5855390223345541964) {
  h_29(state, unused, out_5855390223345541964);
}
void car_H_29(double *state, double *unused, double *out_4932231023786745842) {
  H_29(state, unused, out_4932231023786745842);
}
void car_h_28(double *state, double *unused, double *out_8510755658264266202) {
  h_28(state, unused, out_8510755658264266202);
}
void car_H_28(double *state, double *unused, double *out_6895861295352072093) {
  H_28(state, unused, out_6895861295352072093);
}
void car_h_31(double *state, double *unused, double *out_3677036992164635768) {
  h_31(state, unused, out_3677036992164635768);
}
void car_H_31(double *state, double *unused, double *out_4581984588492554156) {
  H_31(state, unused, out_4581984588492554156);
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
